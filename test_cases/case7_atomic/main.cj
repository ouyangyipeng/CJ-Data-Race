// 测试用例7: Atomic原子操作
// 使用原子类型，无数据竞争

main() {
    let counter = AtomicInt64(0)
    
    // 线程1: 原子加操作
    spawn {
        counter.fetchAdd(1)  // 原子操作，无竞争
    }
    
    // 线程2: 原子加操作
    spawn {
        counter.fetchAdd(1)  // 原子操作，无竞争
    }
    
    println(counter.load())
}