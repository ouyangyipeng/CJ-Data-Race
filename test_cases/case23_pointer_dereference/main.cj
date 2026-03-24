// 测试用例23: 指针解引用竞争
// 测试通过指针访问共享变量的竞争

main() {
    var counter: Int64 = 0
    var ptr = &counter
    
    // 线程1: 通过指针写入
    spawn {
        *ptr = *ptr + 1  // 写操作
    }
    
    // 线程2: 通过指针读取
    spawn {
        let value = *ptr  // 读操作
        println(value)
    }
    
    println(counter)
}