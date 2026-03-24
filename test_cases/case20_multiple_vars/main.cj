// 测试用例20: 多变量竞争
// 测试多个共享变量之间的竞争

main() {
    var counter1: Int64 = 0
    var counter2: Int64 = 0
    var counter3: Int64 = 0
    
    // 线程1: 写入counter1和counter2
    spawn {
        counter1 = counter1 + 1
        counter2 = counter2 + 1
    }
    
    // 线程2: 写入counter2和counter3
    spawn {
        counter2 = counter2 + 1
        counter3 = counter3 + 1
    }
    
    // 线程3: 读取所有变量
    spawn {
        println(counter1)
        println(counter2)
        println(counter3)
    }
    
    println("${counter1}, ${counter2}, ${counter3}")
}