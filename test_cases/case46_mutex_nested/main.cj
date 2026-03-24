// case46: 嵌套锁测试
// 测试嵌套锁的使用（无竞争）

main() {
    var data1: Int64 = 0
    var data2: Int64 = 0
    let mutex1 = Mutex()
    let mutex2 = Mutex()
    
    spawn {
        mutex1.lock()
        mutex2.lock()
        data1 = data1 + 1
        data2 = data2 + 1
        mutex2.unlock()
        mutex1.unlock()
    }
    
    spawn {
        mutex1.lock()
        mutex2.lock()
        data1 = data1 + 2
        data2 = data2 + 2
        mutex2.unlock()
        mutex1.unlock()
    }
}